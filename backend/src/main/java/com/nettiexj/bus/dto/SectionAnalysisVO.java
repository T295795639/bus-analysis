package com.nettiexj.bus.dto;

import lombok.Data;
import java.util.List;

@Data
public class SectionAnalysisVO {
    private String sectionId;
    private String sectionName;
    private Double avgDuration;   // 秒
    private Double anomalyScore;
    private List<double[]> path;  // [[lng,lat], ...]
}
