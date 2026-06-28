package server

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"example.com/ingest/enrich"
	"example.com/ingest/filter"
	"example.com/ingest/metrics"
)

type IngestHandler struct {
	engine   *filter.Engine
	enricher *enrich.Enricher
	stats    *metrics.Collector
	decPool  *sync.Pool
}

func NewIngestHandler(e *filter.Engine, en *enrich.Enricher, st *metrics.Collector) *IngestHandler {
	return &IngestHandler{
		engine:   e,
		enricher: en,
		stats:    st,
		decPool: &sync.Pool{
			New: func() any { return make([]*filter.Event, 0, 256) },
		},
	}
}

type batchRequest struct {
	Events []*filter.Event `json:"events"`
}

type batchResponse struct {
	Accepted int `json:"accepted"`
	Dropped  int `json:"dropped"`
}

func (h *IngestHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	start := time.Now()
	defer func() { h.stats.ObserveLatency(time.Since(start)) }()

	var req batchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	kept := h.decPool.Get().([]*filter.Event)
	kept = kept[:0]
	defer h.decPool.Put(kept)

	var dropped int
	for _, ev := range req.Events {
		if ev == nil {
			continue
		}
		if !h.engine.Apply(ev) {
			dropped++
			h.stats.IncDropped(ev.Source)
			continue
		}
		h.enricher.Enrich(ev)
		kept = append(kept, ev)
	}

	h.stats.AddAccepted(len(kept))

	resp := batchResponse{Accepted: len(kept), Dropped: dropped}
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.stats.IncEncodeError()
	}
}
