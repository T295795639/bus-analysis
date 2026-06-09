package com.nettiexj.bus.service;

import com.nettiexj.bus.dto.RouteVO;
import com.nettiexj.bus.dto.StationParkingAvgVO;
import com.nettiexj.bus.dto.StationRankVO;
import com.nettiexj.bus.dto.StationVO;
import com.nettiexj.bus.entity.Station;
import com.nettiexj.bus.mapper.StationMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class StationService {

    @Autowired
    private StationMapper stationMapper;

    public List<StationVO> listAllWithRouteCount() {
        return stationMapper.selectAllWithRouteCount();
    }

    public List<RouteVO> listRoutesByStationId(Integer stationId) {
        return stationMapper.selectRoutesByStationId(stationId);
    }

    public List<Station> listStationsByRouteId(Integer routeId) {
        return stationMapper.selectStationsByRouteId(routeId);
    }

    public List<StationRankVO> topStationsByParkingCount(Integer topN) {
        if (topN == null || topN <= 0) topN = 20;
        return stationMapper.selectTopByParkingCount(topN);
    }

    public List<StationParkingAvgVO> topStationsByParkingAvgDuration(Integer topN) {
        if (topN == null || topN <= 0) topN = 20;
        return stationMapper.selectTopByParkingAvgDuration(topN);
    }
}
