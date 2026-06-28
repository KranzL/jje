package filter

import "testing"

func sampleRuleSet(t *testing.T) *RuleSet {
	t.Helper()
	rs, err := CompileRules([]RuleSpec{
		{Name: "internal", Field: "source", Match: "prefix", Value: "svc-"},
		{Name: "pii", Field: "body", Match: "regex", Value: `ssn=\d{9}`},
		{Name: "health", Field: "path", Match: "exact", Value: "/healthz"},
	})
	if err != nil {
		t.Fatalf("compile: %v", err)
	}
	return rs
}

func TestEngineApplyTags(t *testing.T) {
	rs := sampleRuleSet(t)
	eng := NewEngine(rs, []string{"blocked"})

	ev := &Event{
		ID:     "1",
		Source: "svc-auth",
		Fields: map[string]string{"source": "svc-auth", "body": "ssn=123456789"},
	}
	if !eng.Apply(ev) {
		t.Fatal("expected event kept")
	}
	if len(ev.Tags) != 2 {
		t.Fatalf("want 2 tags, got %v", ev.Tags)
	}
	if ev.Tags[0] != "internal" || ev.Tags[1] != "pii" {
		t.Fatalf("unexpected tags %v", ev.Tags)
	}
}

func TestEngineDropList(t *testing.T) {
	rs := sampleRuleSet(t)
	eng := NewEngine(rs, []string{"blocked"})
	ev := &Event{ID: "2", Source: "blocked", Fields: map[string]string{}}
	if eng.Apply(ev) {
		t.Fatal("expected drop")
	}
}

func TestAppendUniqueDedupes(t *testing.T) {
	tags := []string{"a"}
	tags = appendUnique(tags, "a")
	tags = appendUnique(tags, "b")
	if len(tags) != 2 {
		t.Fatalf("want 2, got %v", tags)
	}
}
