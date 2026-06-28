package service

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log"

	ledger "github.com/example/ledger"
	"github.com/example/ledger/store"
)

type TransferRequest struct {
	IdempotencyKey string
	FromID         string
	ToID           string
	Amount         int64
	Reference      string
}

type TransferService struct {
	accounts  *store.AccountStore
	transfers *store.TransferStore
	metrics   MetricsSink
}

type MetricsSink interface {
	Incr(name string)
}

func NewTransferService(a *store.AccountStore, t *store.TransferStore, m MetricsSink) *TransferService {
	return &TransferService{accounts: a, transfers: t, metrics: m}
}

func (s *TransferService) Transfer(ctx context.Context, req TransferRequest) (*store.TransferRecord, error) {
	if err := validate(req); err != nil {
		return nil, err
	}

	from, err := s.accounts.Get(ctx, req.FromID)
	if err != nil {
		if errors.Is(err, ledger.ErrAccountNotFound) {
			return nil, fmt.Errorf("source account: %w", err)
		}
		return nil, fmt.Errorf("load source account: %w", err)
	}

	to, err := s.accounts.Get(ctx, req.ToID)
	if err != nil {
		if errors.Is(err, ledger.ErrAccountNotFound) {
			return nil, fmt.Errorf("destination account: %w", err)
		}
		return nil, fmt.Errorf("load destination account: %w", err)
	}

	if from.Frozen {
		return nil, fmt.Errorf("source %s: %w", from.ID, ledger.ErrAccountFrozen)
	}
	if from.Balance < req.Amount {
		return nil, fmt.Errorf("source %s short by %d: %w", from.ID, req.Amount-from.Balance, ledger.ErrInsufficientFunds)
	}

	rec := store.TransferRecord{
		ID:        req.IdempotencyKey,
		FromID:    from.ID,
		ToID:      to.ID,
		Amount:    req.Amount,
		Reference: req.Reference,
	}

	if err := s.run(ctx, rec); err != nil {
		if errors.Is(err, ledger.ErrDuplicateTransfer) {
			s.metrics.Incr("transfer.idempotent_replay")
			return &rec, nil
		}
		return nil, err
	}

	s.metrics.Incr("transfer.committed")
	return &rec, nil
}

func (s *TransferService) run(ctx context.Context, rec store.TransferRecord) (err error) {
	tx, err := s.transfers.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() {
		if err != nil {
			if rbErr := tx.Rollback(); rbErr != nil && !errors.Is(rbErr, sql.ErrTxDone) {
				log.Printf("transfer %s: rollback failed: %v", rec.ID, rbErr)
			}
		}
	}()

	if err = s.transfers.Insert(ctx, tx, rec); err != nil {
		return err
	}
	if err = s.accounts.UpdateBalance(ctx, tx, rec.FromID, -rec.Amount); err != nil {
		return err
	}
	if err = s.accounts.UpdateBalance(ctx, tx, rec.ToID, rec.Amount); err != nil {
		return err
	}

	if err = tx.Commit(); err != nil {
		return fmt.Errorf("commit transfer %s: %w", rec.ID, err)
	}

	return nil
}

func validate(req TransferRequest) error {
	if req.IdempotencyKey == "" {
		return &ledger.ValidationError{Field: "idempotency_key", Reason: "required"}
	}
	if req.FromID == req.ToID {
		return &ledger.ValidationError{Field: "to_id", Reason: "must differ from from_id"}
	}
	if req.Amount <= 0 {
		return &ledger.ValidationError{Field: "amount", Reason: "must be positive"}
	}
	return nil
}
