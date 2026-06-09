package com.nettiexj.bus.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("route")
public class Route {
    @TableId(value = "route_id", type = IdType.INPUT)
    private Integer routeId;

    private String routeName;

    private String isUpOrDown;
}
