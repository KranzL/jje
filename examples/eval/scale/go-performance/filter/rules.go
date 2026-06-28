package filter

import (
	"regexp"
	"strings"
)

type MatchKind int

const (
	MatchExact MatchKind = iota
	MatchPrefix
	MatchRegex
)

type Rule struct {
	Name    string
	Kind    MatchKind
	Field   string
	Literal string
	pattern *regexp.Regexp
}

type RuleSet struct {
	rules   []Rule
	byField map[string][]int
}

func CompileRules(specs []RuleSpec) (*RuleSet, error) {
	rs := &RuleSet{byField: make(map[string][]int, len(specs))}
	for _, spec := range specs {
		r := Rule{
			Name:    spec.Name,
			Field:   spec.Field,
			Literal: spec.Value,
		}
		switch strings.ToLower(spec.Match) {
		case "prefix":
			r.Kind = MatchPrefix
		case "regex":
			r.Kind = MatchRegex
			re, err := regexp.Compile(spec.Value)
			if err != nil {
				return nil, err
			}
			r.pattern = re
		default:
			r.Kind = MatchExact
		}
		idx := len(rs.rules)
		rs.rules = append(rs.rules, r)
		rs.byField[spec.Field] = append(rs.byField[spec.Field], idx)
	}
	return rs, nil
}

type RuleSpec struct {
	Name  string
	Field string
	Match string
	Value string
}

func (rs *RuleSet) Match(field, value string) (string, bool) {
	for _, idx := range rs.byField[field] {
		r := rs.rules[idx]
		switch r.Kind {
		case MatchExact:
			if value == r.Literal {
				return r.Name, true
			}
		case MatchPrefix:
			if strings.HasPrefix(value, r.Literal) {
				return r.Name, true
			}
		case MatchRegex:
			if r.pattern.MatchString(value) {
				return r.Name, true
			}
		}
	}
	return "", false
}

func (rs *RuleSet) Len() int { return len(rs.rules) }
