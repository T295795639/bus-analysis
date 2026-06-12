package com.nettiexj.bus.dto;

import lombok.Data;

/** Mapper 中间对象，path 为原始 JSON 字符串 */
@Data
public class SectionAnalysisRawVO {
    private String sectionId;
    private String sectionName;
    private String path;          // JSON 字符串，如 "[[lng,lat],...]"
    private Double avgDuration;
}
