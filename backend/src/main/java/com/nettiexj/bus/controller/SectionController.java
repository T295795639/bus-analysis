package com.nettiexj.bus.controller;

import com.nettiexj.bus.dto.Result;
import com.nettiexj.bus.dto.SectionDrivingVO;
import com.nettiexj.bus.dto.SectionPathVO;
import com.nettiexj.bus.service.SectionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/section")
public class SectionController {

    @Autowired
    private SectionService sectionService;

    /**
     * 路段行驶时长统计
     * timeRange: all | morning_peak (7-9) | evening_peak (17-19)
     * topN: 返回最慢的前 N 条路段
     */
    /** 按线路获取有序路段 path，用于地图真实路形绘制 */
    @GetMapping("/by-route/{routeId}")
    public Result<List<SectionPathVO>> pathsByRoute(@PathVariable Integer routeId) {
        return Result.success(sectionService.getPathsByRouteId(routeId));
    }

    @GetMapping("/driving/stats")
    public Result<List<SectionDrivingVO>> drivingStats(
            @RequestParam(defaultValue = "all") String timeRange,
            @RequestParam(defaultValue = "50") Integer topN) {
        return Result.success(sectionService.getDrivingStats(timeRange, topN));
    }
}
