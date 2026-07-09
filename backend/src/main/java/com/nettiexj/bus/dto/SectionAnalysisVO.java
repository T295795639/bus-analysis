package com.nettiexj.bus.dto;

import lombok.Data;

import java.util.List;

@Data
public class SectionAnalysisVO {
    private String routeNumber;
    private String sectionId;
    private String sectionName;
    private Integer startStationId;
    private Integer endStationId;
    private Double avgDuration;
    private Double anomalyScore;
    private Long recordCount;
    private List<double[]> path;
}
