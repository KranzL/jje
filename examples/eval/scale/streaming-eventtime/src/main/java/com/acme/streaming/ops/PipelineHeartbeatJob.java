package com.acme.streaming.ops;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingProcessingTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;

public class PipelineHeartbeatJob {

    public static void main(String[] args) throws Exception {
        ParameterTool params = ParameterTool.fromArgs(args);

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(params.getInt("parallelism", 2));

        KafkaSource<byte[]> source = KafkaSource.<byte[]>builder()
                .setBootstrapServers(params.getRequired("kafka.bootstrap"))
                .setTopics(params.get("orders.topic", "orders.v2"))
                .setGroupId("pipeline-heartbeat")
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new RawBytesDeserializer())
                .build();

        DataStream<byte[]> rawRecords = env
                .fromSource(source, WatermarkStrategy.noWatermarks(), "heartbeat-source")
                .name("heartbeat-source");

        rawRecords
                .map(record -> 1L)
                .windowAll(TumblingProcessingTimeWindows.of(Time.minutes(1)))
                .aggregate(new CountAggregator())
                .name("ingest-throughput-per-wallclock-minute")
                .sinkTo(MetricsSinkFactory.gauge(params, "pipeline.ingest.records_per_minute"))
                .name("heartbeat-sink");

        env.execute("pipeline-heartbeat");
    }

    private static final class CountAggregator implements AggregateFunction<Long, Long, Long> {
        @Override
        public Long createAccumulator() {
            return 0L;
        }

        @Override
        public Long add(Long value, Long acc) {
            return acc + value;
        }

        @Override
        public Long getResult(Long acc) {
            return acc;
        }

        @Override
        public Long merge(Long a, Long b) {
            return a + b;
        }
    }
}
