package com.nettiexj.bus.service;

import com.nettiexj.bus.dto.RouteStationDetailVO;
import com.nettiexj.bus.entity.Route;
import com.nettiexj.bus.mapper.RouteMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RouteService {

    @Autowired
    private RouteMapper routeMapper;

    public List<Route> listAll() {
        return routeMapper.selectList(null);
    }

    public List<RouteStationDetailVO> getRouteDetail(Integer routeId) {
        return routeMapper.selectStationsWithParking(routeId);
    }
}
