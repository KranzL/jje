package metrics

import (
	"sync"
	"sync/atomic"
	"time"
)

type Collector struct {
	accepted     atomic.Int64
	encodeErrors atomic.Int64

	mu       sync.Mutex
	dropped  map[string]int64
	latNanos int64
	latCount int64
}

func NewCollector() *Collector {
	return &Collector{dropped: make(map[string]int64, 16)}
}

func (c *Collector) AddAccepted(n int) {
	c.accepted.Add(int64(n))
}

func (c *Collector) IncDropped(source string) {
	c.mu.Lock()
	c.dropped[source]++
	c.mu.Unlock()
}

func (c *Collector) IncEncodeError() {
	c.encodeErrors.Add(1)
}

func (c *Collector) ObserveLatency(d time.Duration) {
	c.mu.Lock()
	c.latNanos += int64(d)
	c.latCount++
	c.mu.Unlock()
}

type Snapshot struct {
	Accepted     int64
	EncodeErrors int64
	Dropped      map[string]int64
	MeanLatency  time.Duration
}

func (c *Collector) Snapshot() Snapshot {
	c.mu.Lock()
	defer c.mu.Unlock()

	dropped := make(map[string]int64, len(c.dropped))
	for k, v := range c.dropped {
		dropped[k] = v
	}
	var mean time.Duration
	if c.latCount > 0 {
		mean = time.Duration(c.latNanos / c.latCount)
	}
	return Snapshot{
		Accepted:     c.accepted.Load(),
		EncodeErrors: c.encodeErrors.Load(),
		Dropped:      dropped,
		MeanLatency:  mean,
	}
}
