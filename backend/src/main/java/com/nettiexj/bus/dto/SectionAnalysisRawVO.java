package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class SectionAnalysisRawVO {
    private String routeNumber;
    private String sectionId;
    private String sectionName;
    private Integer startStationId;
    private Integer endStationId;
    private String path;
    private Double avgDuration;
    private Long recordCount;
}
