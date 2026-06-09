package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class StationParkingAvgVO {
    private Integer stationId;
    private String stationName;
    private Double lng;
    private Double lat;
    private Double avgDurationSeconds;
    private Long parkingCount;
}
