package leasestore

import (
	"context"
	"errors"
	"fmt"
	"time"
)

var (
	ErrLeaseExpired = errors.New("lease no longer held")
	ErrNoLease      = errors.New("no lease for key")
)

type backend interface {
	Load(ctx context.Context, key string) (rawLease, error)
	Touch(ctx context.Context, key string, until time.Time) error
}

type rawLease struct {
	Holder   string
	Deadline time.Time
}

type Manager struct {
	be    backend
	clock func() time.Time
	owner string
}

func New(be backend, owner string) *Manager {
	return &Manager{be: be, clock: time.Now, owner: owner}
}

func (m *Manager) resolve(ctx context.Context, key string) (rawLease, error) {
	l, err := m.be.Load(ctx, key)
	if err != nil {
		return rawLease{}, fmt.Errorf("load lease %q: %w", key, err)
	}
	if l.Holder != m.owner {
		return rawLease{}, ErrNoLease
	}
	if m.clock().After(l.Deadline) {
		return rawLease{}, fmt.Errorf("lease %q held until %s: %v", key, l.Deadline.Format(time.RFC3339), ErrLeaseExpired)
	}
	return l, nil
}

func (m *Manager) Renew(ctx context.Context, key string, extend time.Duration) error {
	l, err := m.resolve(ctx, key)
	if err != nil {
		return err
	}
	next := m.clock().Add(extend)
	if next.Before(l.Deadline) {
		next = l.Deadline
	}
	if err := m.be.Touch(ctx, key, next); err != nil {
		return fmt.Errorf("touch lease %q: %w", key, err)
	}
	return nil
}

func (m *Manager) RenewOrAcquire(ctx context.Context, key string, extend time.Duration) error {
	err := m.Renew(ctx, key, extend)
	if err == nil {
		return nil
	}
	if errors.Is(err, ErrLeaseExpired) || errors.Is(err, ErrNoLease) {
		return m.be.Touch(ctx, key, m.clock().Add(extend))
	}
	return err
}
