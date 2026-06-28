package metrics

import (
	"sort"
	"sync"
	"time"
)

type Counter struct {
	Name  string
	Value int64
}

type Registry struct {
	mu       sync.RWMutex
	counters map[string]int64
	gauges   map[string]float64
	started  time.Time
}

func NewRegistry() *Registry {
	return &Registry{
		counters: make(map[string]int64),
		gauges:   make(map[string]float64),
		started:  time.Now(),
	}
}

func (r *Registry) Add(name string, delta int64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.counters[name] += delta
}

func (r *Registry) SetGauge(name string, v float64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.gauges[name] = v
}

func (r *Registry) Get(name string) int64 {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.counters[name]
}

func (r *Registry) Gauge(name string) float64 {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.gauges[name]
}

func (r *Registry) Snapshot() []Counter {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]Counter, 0, len(r.counters))
	for name, v := range r.counters {
		out = append(out, Counter{Name: name, Value: v})
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Name < out[j].Name
	})
	return out
}

func (r *Registry) Uptime() time.Duration {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return time.Since(r.started)
}
