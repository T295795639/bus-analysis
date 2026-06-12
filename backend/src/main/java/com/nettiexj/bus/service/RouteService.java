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

import java.util.List;

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
        double stationAvg = stations.stream()
                .mapToDouble(s -> s.getAvgDuration() == null ? 0 : s.getAvgDuration())
                .filter(v -> v > 0).average().orElse(1);
        stations.forEach(s -> {
            double d = s.getAvgDuration() == null ? 0 : s.getAvgDuration();
            s.setAnomalyScore(stationAvg > 0 ? d / stationAvg : 0);
        });

        // 2. 路段（path 为 JSON 字符串，转换后填入 SectionAnalysisVO）
        List<SectionAnalysisRawVO> rawSections = sectionMapper.selectSectionAnalysisByRouteId(routeId);
        double sectionAvg = rawSections.stream()
                .mapToDouble(s -> s.getAvgDuration() == null ? 0 : s.getAvgDuration())
                .filter(v -> v > 0).average().orElse(1);
        List<SectionAnalysisVO> sections = rawSections.stream().map(raw -> {
            SectionAnalysisVO s = new SectionAnalysisVO();
            s.setSectionId(raw.getSectionId());
            s.setSectionName(raw.getSectionName());
            double d = raw.getAvgDuration() == null ? 0 : raw.getAvgDuration();
            s.setAvgDuration(d);
            s.setAnomalyScore(sectionAvg > 0 ? d / sectionAvg : 0);
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

        RouteAnalysisVO vo = new RouteAnalysisVO();
        vo.setStations(stations);
        vo.setSections(sections);
        vo.setStationAvg(stationAvg);
        vo.setSectionAvg(sectionAvg);
        return vo;
    }
}
