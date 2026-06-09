package com.nettiexj.bus.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("station")
public class Station {
    @TableId(value = "station_id", type = IdType.INPUT)
    private Integer stationId;

    private String stationName;

    private Double lng;

    private Double lat;
}
