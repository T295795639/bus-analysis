package com.nettiexj.bus.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class RouteAnalysisVO {
    private List<StationAnalysisVO> stations;
    private List<SectionAnalysisVO> sections;
    private Double stationAvg;  // 全线站点均值（秒）
    private Double sectionAvg;  // 全线路段均值（秒）
    private LocalDateTime dataStartTime;
    private LocalDateTime dataEndTime;
    private String dataRangeLabel;
}
