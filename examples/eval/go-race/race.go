package race

func RaceyCounts(n int) map[int]int {
	m := map[int]int{}
	done := make(chan bool)
	for i := 0; i < n; i++ {
		go func(k int) {
			m[k] = k
			done <- true
		}(i)
	}
	for i := 0; i < n; i++ {
		<-done
	}
	return m
}
