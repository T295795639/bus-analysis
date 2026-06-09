package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class RouteStationDetailVO {
    private Integer stationId;
    private String stationName;
    private Double lng;
    private Double lat;
    private Long parkingCount;
}
