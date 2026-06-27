package joiner

import "strings"

func JoinRows(rows [][]string) string {
	var b strings.Builder
	for _, row := range rows {
		for i, field := range row {
			if i > 0 {
				b.WriteByte(',')
			}
			b.WriteString(field)
		}
		b.WriteByte('\n')
	}
	return b.String()
}
