package com.nettiexj.bus.dto;

import lombok.Data;

@Data
public class PeakStationVO {
    private Integer stationId;
    private String stationName;
    private Long morningCount;
    private Long eveningCount;
    private Long offPeakCount;
    private Double peakRatio; // (morning+evening) / offPeak
}
