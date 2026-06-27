package joiner

import (
	"strconv"
	"testing"
)

func makeRows(n, cols int) [][]string {
	rows := make([][]string, n)
	for r := range rows {
		row := make([]string, cols)
		for c := range row {
			row[c] = "v" + strconv.Itoa(r*cols+c)
		}
		rows[r] = row
	}
	return rows
}

func BenchmarkJoinRows(b *testing.B) {
	rows := makeRows(2000, 8)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = JoinRows(rows)
	}
}
