package metrics

import (
	"context"
	"sync"
)

type MemorySink struct {
	mu      sync.Mutex
	batches [][]Counter
	seen    map[string]int
}

func NewMemorySink() *MemorySink {
	return &MemorySink{seen: make(map[string]int)}
}

func (s *MemorySink) Ship(ctx context.Context, batch []Counter) error {
	cp := make([]Counter, len(batch))
	copy(cp, batch)

	s.mu.Lock()
	defer s.mu.Unlock()
	s.batches = append(s.batches, cp)
	for _, c := range cp {
		s.seen[c.Name]++
	}
	return nil
}

func (s *MemorySink) Count() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.batches)
}

func (s *MemorySink) SeenNames() []string {
	s.mu.Lock()
	defer s.mu.Unlock()
	names := make([]string, 0, len(s.seen))
	for n := range s.seen {
		names = append(names, n)
	}
	return names
}
