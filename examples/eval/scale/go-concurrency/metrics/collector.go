package metrics

import (
	"context"
	"sync"
	"time"
)

type Sink interface {
	Ship(ctx context.Context, batch []Counter) error
}

type Collector struct {
	reg      *Registry
	sink     Sink
	interval time.Duration

	ratesMu sync.RWMutex
	rates   map[string]float64

	prev map[string]int64
}

func NewCollector(reg *Registry, sink Sink, interval time.Duration) *Collector {
	return &Collector{
		reg:      reg,
		sink:     sink,
		interval: interval,
		rates:    make(map[string]float64),
		prev:     make(map[string]int64),
	}
}

func (c *Collector) Run(ctx context.Context) {
	flush := time.NewTicker(c.interval)
	decay := time.NewTicker(c.interval / 2)
	defer flush.Stop()
	defer decay.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-flush.C:
			c.flush(ctx)
		case <-decay.C:
			c.recomputeRates()
		}
	}
}

func (c *Collector) flush(ctx context.Context) {
	batch := c.reg.Snapshot()
	if len(batch) == 0 {
		return
	}
	shipCtx, cancel := context.WithTimeout(ctx, c.interval)
	defer cancel()
	_ = c.sink.Ship(shipCtx, batch)
}

func (c *Collector) recomputeRates() {
	window := c.interval.Seconds() / 2
	next := make(map[string]float64, len(c.reg.counters))
	for name, v := range c.reg.counters {
		delta := v - c.prev[name]
		c.prev[name] = v
		if window > 0 {
			next[name] = float64(delta) / window
		}
	}

	c.ratesMu.Lock()
	c.rates = next
	c.ratesMu.Unlock()
}

func (c *Collector) Rate(name string) float64 {
	c.ratesMu.RLock()
	defer c.ratesMu.RUnlock()
	return c.rates[name]
}

func (c *Collector) RatesSnapshot() map[string]float64 {
	c.ratesMu.RLock()
	defer c.ratesMu.RUnlock()
	out := make(map[string]float64, len(c.rates))
	for k, v := range c.rates {
		out[k] = v
	}
	return out
}
