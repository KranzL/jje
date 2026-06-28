package enrich

import (
	"regexp"
	"strings"

	"example.com/ingest/filter"
)

var (
	ipv4Pattern  = regexp.MustCompile(`\b\d{1,3}(?:\.\d{1,3}){3}\b`)
	emailPattern = regexp.MustCompile(`[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`)
)

type RedactPattern struct {
	Label string
	Expr  string
}

type Enricher struct {
	geo      *GeoTable
	redact   []RedactPattern
	hostName string
}

func New(geo *GeoTable, redact []RedactPattern, host string) *Enricher {
	return &Enricher{
		geo:      geo,
		redact:   redact,
		hostName: host,
	}
}

func (e *Enricher) Enrich(ev *filter.Event) {
	if ev.Fields == nil {
		ev.Fields = make(map[string]string, 2)
	}
	ev.Fields["ingest_host"] = e.hostName

	if ip := ev.Fields["client_ip"]; ip != "" && ipv4Pattern.MatchString(ip) {
		if region, ok := e.geo.Lookup(ip); ok {
			ev.Fields["client_region"] = region
		}
	}

	for field, value := range ev.Fields {
		if !strings.HasSuffix(field, "_raw") {
			continue
		}
		ev.Fields[field] = e.redactValue(value)
	}
}

func (e *Enricher) redactValue(value string) string {
	if value == "" {
		return value
	}
	out := value
	if emailPattern.MatchString(out) {
		out = emailPattern.ReplaceAllString(out, "[email]")
	}
	for _, p := range e.redact {
		re, err := regexp.Compile(p.Expr)
		if err != nil {
			continue
		}
		if re.MatchString(out) {
			out = re.ReplaceAllString(out, "["+p.Label+"]")
		}
	}
	return out
}
