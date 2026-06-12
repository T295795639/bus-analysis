package com.nettiexj.bus.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nettiexj.bus.dto.RouteStationDetailVO;
import com.nettiexj.bus.entity.Route;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface RouteMapper extends BaseMapper<Route> {

    List<RouteStationDetailVO> selectStationsWithParking(@Param("routeId") Integer routeId);

    List<com.nettiexj.bus.dto.RouteVO> selectRoutesByClusterId(@Param("clusterId") Integer clusterId);
}
