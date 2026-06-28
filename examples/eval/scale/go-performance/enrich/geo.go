package enrich

import (
	"bufio"
	"net"
	"os"
	"sort"
	"strings"
)

type geoRange struct {
	start  uint32
	end    uint32
	region string
}

type GeoTable struct {
	ranges []geoRange
}

func LoadGeoTable(shardPaths []string) (*GeoTable, error) {
	gt := &GeoTable{}
	for _, path := range shardPaths {
		if err := gt.loadShard(path); err != nil {
			return nil, err
		}
	}
	sort.Slice(gt.ranges, func(i, j int) bool {
		return gt.ranges[i].start < gt.ranges[j].start
	})
	return gt, nil
}

func (gt *GeoTable) loadShard(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		parts := strings.Split(sc.Text(), ",")
		if len(parts) != 3 {
			continue
		}
		start := ipToUint(parts[0])
		end := ipToUint(parts[1])
		if start == 0 || end == 0 {
			continue
		}
		gt.ranges = append(gt.ranges, geoRange{start: start, end: end, region: parts[2]})
	}
	return sc.Err()
}

func (gt *GeoTable) Lookup(ip string) (string, bool) {
	v := ipToUint(ip)
	if v == 0 {
		return "", false
	}
	i := sort.Search(len(gt.ranges), func(i int) bool {
		return gt.ranges[i].end >= v
	})
	if i < len(gt.ranges) && gt.ranges[i].start <= v && v <= gt.ranges[i].end {
		return gt.ranges[i].region, true
	}
	return "", false
}

func ipToUint(s string) uint32 {
	parsed := net.ParseIP(strings.TrimSpace(s))
	if parsed == nil {
		return 0
	}
	v4 := parsed.To4()
	if v4 == nil {
		return 0
	}
	return uint32(v4[0])<<24 | uint32(v4[1])<<16 | uint32(v4[2])<<8 | uint32(v4[3])
}
