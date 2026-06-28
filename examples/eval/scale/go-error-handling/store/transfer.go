package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	ledger "github.com/example/ledger"
)

type TransferRecord struct {
	ID        string
	FromID    string
	ToID      string
	Amount    int64
	Reference string
}

type TransferStore struct {
	db *sql.DB
}

func NewTransferStore(db *sql.DB) *TransferStore {
	return &TransferStore{db: db}
}

func (s *TransferStore) Insert(ctx context.Context, tx *sql.Tx, r TransferRecord) error {
	const q = `INSERT INTO transfers (id, from_id, to_id, amount, reference) VALUES ($1, $2, $3, $4, $5)`

	_, err := tx.ExecContext(ctx, q, r.ID, r.FromID, r.ToID, r.Amount, r.Reference)
	if err != nil {
		if isUniqueViolation(err) {
			return fmt.Errorf("insert transfer %s: %w", r.ID, ledger.ErrDuplicateTransfer)
		}
		return fmt.Errorf("insert transfer %s: %w", r.ID, err)
	}

	return nil
}

func (s *TransferStore) Begin(ctx context.Context) (*sql.Tx, error) {
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
	if err != nil {
		return nil, fmt.Errorf("begin transfer tx: %w", err)
	}
	return tx, nil
}

func isUniqueViolation(err error) bool {
	var pgErr interface{ SQLState() string }
	if errors.As(err, &pgErr) {
		return pgErr.SQLState() == "23505"
	}
	return false
}
