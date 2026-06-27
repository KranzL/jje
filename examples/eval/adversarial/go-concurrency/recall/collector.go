package collector

import (
	"sort"
	"sync"
	"time"
)

type Collector struct {
	mu     sync.Mutex
	hits   map[string]int64
	total  int64
	closed bool
}

func New() *Collector {
	return &Collector{hits: make(map[string]int64)}
}

func (c *Collector) Record(label string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.closed {
		return
	}
	c.hits[label]++
	c.total++
}

func (c *Collector) TopN(n int) []string {
	c.mu.Lock()
	defer c.mu.Unlock()
	labels := make([]string, 0, len(c.hits))
	for k := range c.hits {
		labels = append(labels, k)
	}
	sort.Slice(labels, func(i, j int) bool {
		return c.hits[labels[i]] > c.hits[labels[j]]
	})
	if n > len(labels) {
		n = len(labels)
	}
	return labels[:n]
}

func (c *Collector) Close() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.closed = true
}

type Sample struct {
	At       time.Time
	Distinct int
	Total    int64
}

func (c *Collector) Watch(every time.Duration, out chan<- Sample, stop <-chan struct{}) {
	tick := time.NewTicker(every)
	defer tick.Stop()
	for {
		select {
		case <-stop:
			return
		case now := <-tick.C:
			s := Sample{At: now, Distinct: len(c.hits)}
			c.mu.Lock()
			s.Total = c.total
			c.mu.Unlock()
			select {
			case out <- s:
			case <-stop:
				return
			}
		}
	}
}
