package com.nettiexj.bus.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("section")
public class Section {
    @TableId(value = "section_id", type = IdType.INPUT)
    private String sectionId;        // VARCHAR(50)，如 "101_down_00"

    private Integer startStationId;

    private Integer endStationId;

    private String direction;        // "up" / "down" 等

    private String sectionName;

    private String path;
}
