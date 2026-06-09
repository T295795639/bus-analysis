package com.nettiexj.bus.controller;

import com.nettiexj.bus.dto.Result;
import com.nettiexj.bus.dto.RouteVO;
import com.nettiexj.bus.dto.StationParkingAvgVO;
import com.nettiexj.bus.dto.StationRankVO;
import com.nettiexj.bus.dto.StationVO;
import com.nettiexj.bus.entity.Station;
import com.nettiexj.bus.service.StationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/station")
public class StationController {

    @Autowired
    private StationService stationService;

    /** 所有站点 + 线路数量（用于地图打点和大小编码） */
    @GetMapping("/all")
    public Result<List<StationVO>> listAll() {
        return Result.success(stationService.listAllWithRouteCount());
    }

    /** 某站点的所有途经线路 */
    @GetMapping("/{stationId}/routes")
    public Result<List<RouteVO>> listRoutes(@PathVariable Integer stationId) {
        return Result.success(stationService.listRoutesByStationId(stationId));
    }

    /** 某线路经过的所有站点（用于绘制线路） */
    @GetMapping("/by-route/{routeId}")
    public Result<List<Station>> listByRoute(@PathVariable Integer routeId) {
        return Result.success(stationService.listStationsByRouteId(routeId));
    }

    /** 站点停靠次数 Top N */
    @GetMapping("/ranking")
    public Result<List<StationRankVO>> ranking(@RequestParam(defaultValue = "20") Integer topN) {
        return Result.success(stationService.topStationsByParkingCount(topN));
    }

    /** 站点平均停靠时长 Top N（识别异常站点） */
    @GetMapping("/parking/stats")
    public Result<List<StationParkingAvgVO>> parkingStats(@RequestParam(defaultValue = "20") Integer topN) {
        return Result.success(stationService.topStationsByParkingAvgDuration(topN));
    }
}
