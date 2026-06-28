package transport

import (
	"encoding/json"
	"errors"
	"net/http"

	ledger "github.com/example/ledger"
	"github.com/example/ledger/service"
)

type Handler struct {
	svc *service.TransferService
}

func NewHandler(svc *service.TransferService) *Handler {
	return &Handler{svc: svc}
}

type transferBody struct {
	IdempotencyKey string `json:"idempotency_key"`
	FromID         string `json:"from_id"`
	ToID           string `json:"to_id"`
	Amount         int64  `json:"amount"`
	Reference      string `json:"reference"`
}

func (h *Handler) Transfer(w http.ResponseWriter, r *http.Request) {
	var body transferBody
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	rec, err := h.svc.Transfer(r.Context(), service.TransferRequest{
		IdempotencyKey: body.IdempotencyKey,
		FromID:         body.FromID,
		ToID:           body.ToID,
		Amount:         body.Amount,
		Reference:      body.Reference,
	})
	if err != nil {
		writeError(w, statusFor(err), err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"transfer_id": rec.ID,
		"reference":   rec.Reference,
	})
}

func statusFor(err error) int {
	switch {
	case ledger.IsValidation(err):
		return http.StatusBadRequest
	case errors.Is(err, ledger.ErrAccountNotFound):
		return http.StatusNotFound
	case errors.Is(err, ledger.ErrInsufficientFunds):
		return http.StatusUnprocessableEntity
	case errors.Is(err, ledger.ErrAccountFrozen):
		return http.StatusConflict
	default:
		return http.StatusInternalServerError
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]any{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		return
	}
}
