package com.nettiexj.bus.controller;

import com.nettiexj.bus.dto.Result;
import com.nettiexj.bus.dto.RouteStationDetailVO;
import com.nettiexj.bus.entity.Route;
import com.nettiexj.bus.service.RouteService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/route")
public class RouteController {

    @Autowired
    private RouteService routeService;

    /** 所有线路列表 */
    @GetMapping("/list")
    public Result<List<Route>> list() {
        return Result.success(routeService.listAll());
    }

    /** 线路详情：有序站点 + 各站停靠次数 */
    @GetMapping("/{routeId}/detail")
    public Result<List<RouteStationDetailVO>> detail(@PathVariable Integer routeId) {
        return Result.success(routeService.getRouteDetail(routeId));
    }

    /** 某聚类簇内经过的所有线路 */
    @GetMapping("/by-cluster/{clusterId}")
    public Result<List<com.nettiexj.bus.dto.RouteVO>> byCluster(@PathVariable Integer clusterId) {
        return Result.success(routeService.getRoutesByCluster(clusterId));
    }

    /** 线路瓶颈分析：沿线站点停靠时长 + 路段行驶时长 + 异常评分 */
    @GetMapping("/{routeId}/analysis")
    public Result<com.nettiexj.bus.dto.RouteAnalysisVO> analysis(@PathVariable Integer routeId) {
        return Result.success(routeService.getRouteAnalysis(routeId));
    }
}
