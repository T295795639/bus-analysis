package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class TransferHubVO {
    private Integer stationId;
    private String stationName;
    private Double lng;
    private Double lat;
    private Long routeCount;
    private Long parkingCount;
}
