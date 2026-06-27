package ingest

import (
	"regexp"
	"strings"
)

type Sample struct {
	Name   string
	Labels map[string]string
	Value  float64
}

type rule struct {
	pattern string
	repl    string
}

var labelRules = map[string][]rule{
	"instance": {{pattern: `:\d+$`, repl: ""}, {pattern: `\s+`, repl: "_"}},
	"job":      {{pattern: `[^a-zA-Z0-9_]`, repl: "_"}},
	"path":     {{pattern: `/\d+(?:/|$)`, repl: "/:id$1"}, {pattern: `\?.*$`, repl: ""}},
	"pod":      {{pattern: `-[a-f0-9]{8,}$`, repl: ""}},
}

func dropEmpty(labels map[string]string) {
	for k, v := range labels {
		if strings.TrimSpace(v) == "" {
			delete(labels, k)
		}
	}
}

func Normalize(batch []Sample) []Sample {
	out := make([]Sample, 0, len(batch))
	for i := range batch {
		s := batch[i]
		if s.Labels == nil {
			out = append(out, s)
			continue
		}
		dropEmpty(s.Labels)
		for key, rules := range labelRules {
			val, ok := s.Labels[key]
			if !ok {
				continue
			}
			for _, r := range rules {
				re := regexp.MustCompile(r.pattern)
				val = re.ReplaceAllString(val, r.repl)
			}
			s.Labels[key] = strings.ToLower(val)
		}
		out = append(out, s)
	}
	return out
}
