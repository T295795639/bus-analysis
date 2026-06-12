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

    /** 全量站点停靠散点图数据（停靠次数 × 平均时长） */
    @GetMapping("/parking/scatter")
    public Result<List<StationParkingAvgVO>> parkingScatter() {
        return Result.success(stationService.parkingScatter());
    }

    /** 高峰 vs 平峰停靠量对比 Top N */
    @GetMapping("/peak/comparison")
    public Result<List<com.nettiexj.bus.dto.PeakStationVO>> peakComparison(
            @RequestParam(defaultValue = "20") Integer topN) {
        return Result.success(stationService.peakComparison(topN));
    }

    /** 某站点全天停靠量按小时分布 */
    @GetMapping("/{stationId}/hourly")
    public Result<List<com.nettiexj.bus.dto.HourlyCountVO>> hourly(@PathVariable Integer stationId) {
        return Result.success(stationService.hourlyCount(stationId));
    }

    /** 换乘枢纽识别 Top N */
    @GetMapping("/transfer-hub")
    public Result<List<com.nettiexj.bus.dto.TransferHubVO>> transferHub(
            @RequestParam(defaultValue = "20") Integer topN) {
        return Result.success(stationService.transferHubs(topN));
    }

    /** 各聚类区域停靠时长统计 */
    @GetMapping("/cluster/parking-stats")
    public Result<List<com.nettiexj.bus.dto.ClusterParkingVO>> clusterParkingStats() {
        return Result.success(stationService.clusterParkingStats());
    }
}
