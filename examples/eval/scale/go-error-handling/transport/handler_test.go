package transport

import (
	"fmt"
	"net/http"
	"testing"

	ledger "github.com/example/ledger"
)

func TestStatusFor(t *testing.T) {
	cases := []struct {
		name string
		err  error
		want int
	}{
		{"validation", &ledger.ValidationError{Field: "amount", Reason: "must be positive"}, http.StatusBadRequest},
		{"not_found", fmt.Errorf("source account: %w", ledger.ErrAccountNotFound), http.StatusNotFound},
		{"insufficient", fmt.Errorf("source x short by 5: %w", ledger.ErrInsufficientFunds), http.StatusUnprocessableEntity},
		{"frozen", fmt.Errorf("source x: %w", ledger.ErrAccountFrozen), http.StatusConflict},
		{"unknown", fmt.Errorf("boom"), http.StatusInternalServerError},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := statusFor(tc.err); got != tc.want {
				t.Fatalf("statusFor(%v) = %d, want %d", tc.err, got, tc.want)
			}
		})
	}
}
