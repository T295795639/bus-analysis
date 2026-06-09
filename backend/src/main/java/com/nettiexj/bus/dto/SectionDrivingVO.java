package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class SectionDrivingVO {
    private String sectionId;
    private String sectionName;
    private String direction;
    private Double avgDurationSeconds;
    private Long recordCount;
}
