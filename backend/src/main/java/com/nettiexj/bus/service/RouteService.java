package com.nettiexj.bus.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nettiexj.bus.dto.*;
import com.nettiexj.bus.entity.Route;
import com.nettiexj.bus.mapper.RouteMapper;
import com.nettiexj.bus.mapper.SectionMapper;
import com.nettiexj.bus.mapper.StationMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class RouteService {

    @Autowired private RouteMapper routeMapper;
    @Autowired private StationMapper stationMapper;
    @Autowired private SectionMapper sectionMapper;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<Route> listAll() {
        return routeMapper.selectList(null);
    }

    public List<RouteStationDetailVO> getRouteDetail(Integer routeId) {
        return routeMapper.selectStationsWithParking(routeId);
    }

    public List<RouteVO> getRoutesByCluster(Integer clusterId) {
        return routeMapper.selectRoutesByClusterId(clusterId);
    }

    public RouteAnalysisVO getRouteAnalysis(Integer routeId) {
        // 1. 站点
        List<StationAnalysisVO> stations = stationMapper.selectStationAnalysisByRouteId(routeId);
        stations = mergeMissingRouteStations(stations, stationMapper.selectRouteStationAnalysisByRouteId(routeId));
        normalizeStationDurations(stations);
        double stationAvg = stations.stream()
                .mapToDouble(s -> s.getAvgDuration() == null ? 0 : s.getAvgDuration())
                .filter(v -> v > 0).average().orElse(1);
        stations.forEach(s -> {
            double d = s.getAvgDuration() == null ? 0 : s.getAvgDuration();
            s.setAnomalyScore(stationAvg > 0 ? d / stationAvg : 0);
        });

        // 2. 路段（path 为 JSON 字符串，转换后填入 SectionAnalysisVO）
        List<SectionAnalysisRawVO> rawSections = sectionMapper.selectSectionAnalysisByRouteId(routeId);
        List<SectionAnalysisVO> sections = rawSections.stream().map(raw -> {
            SectionAnalysisVO s = new SectionAnalysisVO();
            s.setRouteNumber(raw.getRouteNumber());
            s.setSectionId(raw.getSectionId());
            s.setSectionName(raw.getSectionName());
            s.setStartStationId(raw.getStartStationId());
            s.setEndStationId(raw.getEndStationId());
            s.setRecordCount(raw.getRecordCount() == null ? 0L : raw.getRecordCount());
            double d = raw.getAvgDuration() == null ? 0 : raw.getAvgDuration();
            s.setAvgDuration(d);
            try {
                if (raw.getPath() != null && !raw.getPath().isBlank()) {
                    s.setPath(objectMapper.readValue(raw.getPath(),
                            new TypeReference<List<double[]>>() {}));
                } else {
                    s.setPath(List.of());
                }
            } catch (Exception e) {
                s.setPath(List.of());
            }
            return s;
        }).toList();
        normalizeSectionDurations(sections);
        double sectionAvg = sections.stream()
                .mapToDouble(s -> s.getAvgDuration() == null ? 0 : s.getAvgDuration())
                .filter(v -> v > 0).average().orElse(1);
        sections.forEach(s -> {
            double d = s.getAvgDuration() == null ? 0 : s.getAvgDuration();
            s.setAnomalyScore(sectionAvg > 0 ? d / sectionAvg : 0);
        });

        RouteAnalysisVO vo = new RouteAnalysisVO();
        vo.setStations(stations);
        vo.setSections(sections);
        vo.setStationAvg(stationAvg);
        vo.setSectionAvg(sectionAvg);
        return vo;
    }

    private void normalizeStationDurations(List<StationAnalysisVO> stations) {
        double[] original = stations.stream()
                .mapToDouble(s -> positiveOrZero(s.getAvgDuration()))
                .toArray();
        double baseline = medianPositive(original);
        for (int i = 0; i < stations.size(); i++) {
            if (original[i] <= 0) {
                stations.get(i).setAvgDuration(estimateDuration(original, i, baseline));
            }
        }
        if (!stations.isEmpty() && original.length > 0 && original[0] > baseline * 3) {
            stations.get(0).setAvgDuration(estimateDuration(original, 0, baseline));
        }
    }

    private void normalizeSectionDurations(List<SectionAnalysisVO> sections) {
        double[] original = sections.stream()
                .mapToDouble(s -> positiveOrZero(s.getAvgDuration()))
                .toArray();
        double baseline = medianPositive(original);
        for (int i = 0; i < sections.size(); i++) {
            if (original[i] <= 0) {
                sections.get(i).setAvgDuration(estimateDuration(original, i, baseline));
            }
        }
        if (!sections.isEmpty() && original.length > 0 && original[0] > baseline * 3) {
            sections.get(0).setAvgDuration(estimateDuration(original, 0, baseline));
        }
    }

    private double positiveOrZero(Double value) {
        return value == null || value <= 0 ? 0 : value;
    }

    private double medianPositive(double[] values) {
        List<Double> positives = new ArrayList<>();
        for (double value : values) {
            if (value > 0) {
                positives.add(value);
            }
        }
        if (positives.isEmpty()) {
            return 60;
        }
        positives.sort(Double::compareTo);
        int mid = positives.size() / 2;
        if (positives.size() % 2 == 1) {
            return positives.get(mid);
        }
        return (positives.get(mid - 1) + positives.get(mid)) / 2.0;
    }

    private double estimateDuration(double[] original, int index, double fallback) {
        Double prev = null;
        Double next = null;
        for (int i = index - 1; i >= 0; i--) {
            if (original[i] > 0) {
                prev = original[i];
                break;
            }
        }
        for (int i = index + 1; i < original.length; i++) {
            if (original[i] > 0) {
                next = original[i];
                break;
            }
        }
        if (prev != null && next != null) {
            return (prev + next) / 2.0;
        }
        if (prev != null) {
            return prev;
        }
        if (next != null) {
            return next;
        }
        return fallback;
    }

    /**
     * section 表提供路线骨架，route_station 可能包含 section 生成时漏掉的真实站点。
     * 对缺失站点按地理位置投影到最近的相邻站点线段中，运行时补回，不直接修改数据库。
     */
    private List<StationAnalysisVO> mergeMissingRouteStations(List<StationAnalysisVO> sectionStations,
                                                              List<StationAnalysisVO> routeStations) {
        if (sectionStations == null || sectionStations.size() < 2 || routeStations == null || routeStations.isEmpty()) {
            return sectionStations;
        }

        Set<Integer> existingIds = new HashSet<>();
        for (StationAnalysisVO station : sectionStations) {
            existingIds.add(station.getStationId());
        }

        Map<Integer, List<Insertion>> insertions = new HashMap<>();
        int routeIndex = 0;
        for (StationAnalysisVO missing : routeStations) {
            routeIndex++;
            if (missing.getStationId() == null || existingIds.contains(missing.getStationId())) {
                continue;
            }
            Insertion insertion = findBestInsertion(missing, sectionStations, routeIndex);
            insertions.computeIfAbsent(insertion.afterIndex, k -> new ArrayList<>()).add(insertion);
            existingIds.add(missing.getStationId());
        }

        if (insertions.isEmpty()) {
            return sectionStations;
        }

        insertions.values().forEach(list ->
                list.sort(Comparator.comparingDouble((Insertion i) -> i.projection).thenComparingInt(i -> i.routeIndex)));

        List<StationAnalysisVO> merged = new ArrayList<>();
        for (int i = 0; i < sectionStations.size(); i++) {
            merged.add(sectionStations.get(i));
            List<Insertion> after = insertions.get(i);
            if (after != null) {
                after.forEach(insertion -> merged.add(insertion.station));
            }
        }
        return merged;
    }

    private Insertion findBestInsertion(StationAnalysisVO station, List<StationAnalysisVO> base, int routeIndex) {
        int bestIndex = 0;
        double bestDistance = Double.MAX_VALUE;
        double bestProjection = 0;
        for (int i = 0; i < base.size() - 1; i++) {
            Projection projection = projectToSegment(station, base.get(i), base.get(i + 1));
            double score = projection.distanceKm + (projection.t <= 0 || projection.t >= 1 ? 0.12 : 0);
            if (score < bestDistance) {
                bestDistance = score;
                bestProjection = projection.t;
                bestIndex = i;
            }
        }
        return new Insertion(station, bestIndex, bestProjection, routeIndex);
    }

    private Projection projectToSegment(StationAnalysisVO point, StationAnalysisVO a, StationAnalysisVO b) {
        double px = point.getLng(), py = point.getLat();
        double ax = a.getLng(), ay = a.getLat();
        double bx = b.getLng(), by = b.getLat();
        double vx = bx - ax, vy = by - ay;
        double wx = px - ax, wy = py - ay;
        double vv = vx * vx + vy * vy;
        double t = vv == 0 ? 0 : Math.max(0, Math.min(1, (wx * vx + wy * vy) / vv));
        double projX = ax + t * vx;
        double projY = ay + t * vy;
        return new Projection(haversineKm(py, px, projY, projX), t);
    }

    private double haversineKm(double lat1, double lng1, double lat2, double lng2) {
        double r = 6371.0;
        double p1 = Math.toRadians(lat1), p2 = Math.toRadians(lat2);
        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);
        double h = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(p1) * Math.cos(p2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return r * 2 * Math.asin(Math.sqrt(h));
    }

    private record Projection(double distanceKm, double t) {}
    private record Insertion(StationAnalysisVO station, int afterIndex, double projection, int routeIndex) {}
}
