package org.waf.pipeline;

import com.google.common.collect.Lists;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import io.lettuce.core.RedisClient;
import io.lettuce.core.api.StatefulRedisConnection;
import io.lettuce.core.api.sync.RedisCommands;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.transforms.GroupByKey;
import org.apache.beam.sdk.transforms.PTransform;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.PCollection;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Type;
import java.util.*;

import static java.lang.System.out;

public class Correlations {
    private static final Logger LOG = LoggerFactory.getLogger(Correlations.class);

    public static class WafKvPair extends DoFn<Map<String, String>, KV<String, Map<String, String>>> {
        @ProcessElement
        public void processElement(ProcessContext c) {
            Map<String, String> document = c.element();

            String waf_replayed = document.get("performed_waf_review");
            if (waf_replayed != null && waf_replayed.equals("REPLAY")) {
                KV<String, Map<String, String>> document_kv = KV.of(document.get("ip"), document);
                c.output(document_kv);
            }
        }
    }

    static class TrackWaf extends PTransform<PCollection<Map<String, String>>, PCollection<String>> {
        private final String  redis_host = "10.132.0.5";

        @Override
        public PCollection<String> expand(PCollection<Map<String, String>> documents) {

            PCollection<KV<String, Map<String, String>>> kv_docs = documents.apply(ParDo.of(new WafKvPair()));

            PCollection<KV<String, Iterable<Map<String, String>>>> grouped_kv_docs = kv_docs.apply(GroupByKey.create());

            PCollection<KV<String, String>> alerts = grouped_kv_docs.apply(ParDo.of(new WafCorrelation(this.redis_host)));

            return alerts.apply(ParDo.of(new SendAlerts(this.redis_host)));
        }
    }

    public static class SendAlerts extends DoFn<KV<String, String>,String> {
        private final String  redis_host;

        public SendAlerts(String redis_host) {
            this.redis_host = redis_host;
        }

        private RedisCommands<String, String> syncCommands;
        @Setup
        public void setup() {
            RedisClient redisClient = RedisClient.create("redis://" + this.redis_host + ":6379/0");
            StatefulRedisConnection<String, String> connection = redisClient.connect();
            this.syncCommands = connection.sync();
        }

        @ProcessElement
        public void processElement(ProcessContext c) {
            KV<String, String> document = c.element();
            String key   = document.getKey();
            String value = document.getValue();

            String redis_alert_key = "waf_alert_sent#" + key + "#" + value;
            String redis_answer = this.syncCommands.get(redis_alert_key);

            if (redis_answer == null) {
                LOG.info("Not sending alert again for " + key);
                String json_string = new Gson().toJson(document);
                c.output(json_string);

                this.syncCommands.set(redis_alert_key, "1");
                this.syncCommands.expire(redis_alert_key, 60*60);
            }
        }

        @Teardown
        public void teardown() {
            this.syncCommands.getStatefulConnection().close();
            this.syncCommands.shutdown(true);
        }
    }

    static class WafCorrelation extends DoFn<KV<String, Iterable<Map<String, String>>>, KV<String, String>> {
        private final String redis_host;
        public WafCorrelation(String redis_host) {
            this.redis_host = redis_host;
        }

        private RedisCommands<String, String> syncCommands;
        @Setup
        public void setup() {
            RedisClient redisClient = RedisClient.create("redis://" + this.redis_host + ":6379/0");
            StatefulRedisConnection<String, String> connection = redisClient.connect();
            this.syncCommands = connection.sync();
        }

        @ProcessElement
        public void processElement(ProcessContext c) {
            String ip = c.element().getKey();

            List<Map<String, String>> document_list = Lists.newArrayList(c.element().getValue());

            Integer trigger_score = 5;
            String redis_trigger_score = this.syncCommands.get("waf_trigger_score");
            if (redis_trigger_score != null) {
                trigger_score = Integer.parseInt(redis_trigger_score);
                LOG.info("Used redis score: " + redis_trigger_score );
            }

            Integer score = 0;
            for (Map<String, String> document : document_list) {
                LOG.info("Looking at document: " + document.toString() );
                String waf_response_str = document.get("waf_replay_answer");

                if (waf_response_str != null) {
                    LOG.info("Looking at response: " + waf_response_str );
                    Type mapType = new TypeToken<Map<String, String>>() {}.getType();
                    Map<String, String> waf_response = new Gson().fromJson(waf_response_str, mapType);
                    String is_attack = waf_response.get("status");
                    if (is_attack != null && is_attack.equals("Attack")) {
                        score += 1;
                        LOG.info("(With trigger score " + trigger_score + ") Incrementing score for ip " + ip + " to: " + score);
                    }
                }
            }

            if (score >= trigger_score) {
                LOG.info("Adding IP " + ip + " to be sent to pubsub");
                KV<String, String> alert_map = KV.of("ip", ip);
                c.output(alert_map);
            }
        }

        @Teardown
        public void teardown() {
            this.syncCommands.getStatefulConnection().close();
        }
    }
}