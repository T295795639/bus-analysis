package com.nettiexj.bus.service;

import com.nettiexj.bus.dto.SectionDrivingVO;
import com.nettiexj.bus.dto.SectionPathVO;
import com.nettiexj.bus.mapper.SectionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class SectionService {

    @Autowired
    private SectionMapper sectionMapper;

    public List<SectionDrivingVO> getDrivingStats(String timeRange, Integer topN) {
        if (topN == null || topN <= 0) topN = 50;
        return sectionMapper.selectDrivingStats(timeRange, topN);
    }

    public List<SectionPathVO> getPathsByStationId(Integer stationId) {
        return sectionMapper.selectPathsByStationId(stationId);
    }

    public List<SectionPathVO> getPathsByRouteId(Integer routeId) {
        return sectionMapper.selectPathsByRouteId(routeId);
    }

    public List<SectionPathVO> getAllPaths() {
        return sectionMapper.selectAllPaths();
    }
}
