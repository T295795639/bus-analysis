package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class ClusterParkingVO {
    private Integer clusterId;
    private Long stationCount;
    private Double avgDurationSeconds;
    private Long totalParkingCount;
}
