package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class StationAnalysisVO {
    private Integer stationId;
    private String stationName;
    private Double lng;
    private Double lat;
    private Double avgDuration;
    private Double anomalyScore;
    private Long parkingCount;
    private String durationSource;
}
