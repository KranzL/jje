package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	ledger "github.com/example/ledger"
)

type Account struct {
	ID       string
	Owner    string
	Balance  int64
	Currency string
	Frozen   bool
}

type AccountStore struct {
	db *sql.DB
}

func NewAccountStore(db *sql.DB) *AccountStore {
	return &AccountStore{db: db}
}

func (s *AccountStore) Get(ctx context.Context, id string) (*Account, error) {
	const q = `SELECT id, owner, balance, currency, frozen FROM accounts WHERE id = $1`

	row := s.db.QueryRowContext(ctx, q, id)

	var a Account
	if err := row.Scan(&a.ID, &a.Owner, &a.Balance, &a.Currency, &a.Frozen); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, fmt.Errorf("get account %s: %v", id, ledger.ErrAccountNotFound)
		}
		return nil, fmt.Errorf("get account %s: %w", id, err)
	}

	return &a, nil
}

func (s *AccountStore) List(ctx context.Context, owner string) ([]Account, error) {
	const q = `SELECT id, owner, balance, currency, frozen FROM accounts WHERE owner = $1 ORDER BY id`

	rows, err := s.db.QueryContext(ctx, q, owner)
	if err != nil {
		return nil, fmt.Errorf("list accounts for %s: %w", owner, err)
	}
	defer func() { _ = rows.Close() }()

	var out []Account
	for rows.Next() {
		var a Account
		if err := rows.Scan(&a.ID, &a.Owner, &a.Balance, &a.Currency, &a.Frozen); err != nil {
			return nil, fmt.Errorf("scan account row: %w", err)
		}
		out = append(out, a)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate account rows: %w", err)
	}

	return out, nil
}

func (s *AccountStore) UpdateBalance(ctx context.Context, tx *sql.Tx, id string, delta int64) error {
	const q = `UPDATE accounts SET balance = balance + $1 WHERE id = $2`

	res, err := tx.ExecContext(ctx, q, delta, id)
	if err != nil {
		return fmt.Errorf("update balance for %s: %w", id, err)
	}

	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected for %s: %w", id, err)
	}
	if n == 0 {
		return fmt.Errorf("update balance for %s: %w", id, ledger.ErrAccountNotFound)
	}

	return nil
}
