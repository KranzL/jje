package ledger

import "errors"

var (
	ErrAccountNotFound   = errors.New("account not found")
	ErrInsufficientFunds = errors.New("insufficient funds")
	ErrAccountFrozen     = errors.New("account is frozen")
	ErrDuplicateTransfer = errors.New("duplicate transfer")
)

type ValidationError struct {
	Field  string
	Reason string
}

func (e *ValidationError) Error() string {
	return "validation failed on " + e.Field + ": " + e.Reason
}

func IsValidation(err error) bool {
	var v *ValidationError
	return errors.As(err, &v)
}
