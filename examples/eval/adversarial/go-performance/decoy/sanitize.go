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
	re   *regexp.Regexp
	repl string
}

func mustRules(specs ...[2]string) []rule {
	rs := make([]rule, len(specs))
	for i, sp := range specs {
		rs[i] = rule{re: regexp.MustCompile(sp[0]), repl: sp[1]}
	}
	return rs
}

var labelRules = map[string][]rule{
	"instance": mustRules([2]string{`:\d+$`, ""}, [2]string{`\s+`, "_"}),
	"job":      mustRules([2]string{`[^a-zA-Z0-9_]`, "_"}),
	"path":     mustRules([2]string{`/\d+(?:/|$)`, "/:id$1"}, [2]string{`\?.*$`, ""}),
	"pod":      mustRules([2]string{`-[a-f0-9]{8,}$`, ""}),
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
				val = r.re.ReplaceAllString(val, r.repl)
			}
			s.Labels[key] = strings.ToLower(val)
		}
		out = append(out, s)
	}
	return out
}
