package com.nettiexj.bus;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.nettiexj.bus.mapper")
public class BusAnalysisApplication {
    public static void main(String[] args) {
        SpringApplication.run(BusAnalysisApplication.class, args);
    }
}
