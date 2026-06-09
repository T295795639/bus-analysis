package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class StationVO {
    private Integer stationId;
    private String stationName;
    private Double lng;
    private Double lat;
    private Integer routeCount;
}
