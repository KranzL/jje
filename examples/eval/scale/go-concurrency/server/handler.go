package server

import (
	"encoding/json"
	"net/http"

	"github.com/acme/telemetry/metrics"
)

type Handler struct {
	reg       *metrics.Registry
	collector *metrics.Collector
}

func NewHandler(reg *metrics.Registry, c *metrics.Collector) *Handler {
	return &Handler{reg: reg, collector: c}
}

func (h *Handler) Routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/metrics", h.handleMetrics)
	mux.HandleFunc("/rates", h.handleRates)
	mux.HandleFunc("/healthz", h.handleHealth)
	return mux
}

func (h *Handler) handleMetrics(w http.ResponseWriter, r *http.Request) {
	snap := h.reg.Snapshot()
	writeJSON(w, http.StatusOK, snap)
}

func (h *Handler) handleRates(w http.ResponseWriter, r *http.Request) {
	rates := h.collector.RatesSnapshot()
	writeJSON(w, http.StatusOK, rates)
}

func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"uptime_seconds": h.reg.Uptime().Seconds(),
	})
}

func writeJSON(w http.ResponseWriter, code int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(body)
}
