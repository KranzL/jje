package filter

import (
	"sort"
	"sync"
)

type Event struct {
	ID     string
	Source string
	Fields map[string]string
	Tags   []string
}

type Engine struct {
	mu       sync.RWMutex
	ruleset  *RuleSet
	dropList map[string]struct{}
}

func NewEngine(rs *RuleSet, drop []string) *Engine {
	dl := make(map[string]struct{}, len(drop))
	for _, d := range drop {
		dl[d] = struct{}{}
	}
	return &Engine{ruleset: rs, dropList: dl}
}

func (e *Engine) Swap(rs *RuleSet) {
	e.mu.Lock()
	e.ruleset = rs
	e.mu.Unlock()
}

func (e *Engine) snapshot() *RuleSet {
	e.mu.RLock()
	rs := e.ruleset
	e.mu.RUnlock()
	return rs
}

func (e *Engine) Apply(ev *Event) bool {
	if _, dropped := e.dropList[ev.Source]; dropped {
		return false
	}
	rs := e.snapshot()
	for field, value := range ev.Fields {
		if name, ok := rs.Match(field, value); ok {
			ev.Tags = appendUnique(ev.Tags, name)
		}
	}
	sort.Strings(ev.Tags)
	return true
}

func appendUnique(tags []string, t string) []string {
	for _, existing := range tags {
		if existing == t {
			return tags
		}
	}
	return append(tags, t)
}
