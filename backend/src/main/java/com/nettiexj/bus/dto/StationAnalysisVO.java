package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class StationAnalysisVO {
    private Integer stationId;
    private String stationName;
    private Double lng;
    private Double lat;
    private Double avgDuration;   // 秒
    private Double anomalyScore;  // 当前值 / 全线均值
}
