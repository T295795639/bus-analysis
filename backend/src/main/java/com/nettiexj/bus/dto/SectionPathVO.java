package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class SectionPathVO {
    private String sectionId;
    private String path; // JSON 数组字符串，由前端解析
}
