package org.waf.pipeline;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;

import java.io.IOException;
import java.lang.reflect.Type;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

public class Enrichment {

    private static Map<String, String> PerformWafEnrichment(Map<String, String> document, HttpURLConnection con) throws IOException {

        if (document.get("performed_waf_review") == null) {
            String method = document.get("method");
            String path = document.get("full_path");
            String headers = document.get("headers");
            String data = document.get("data");
            String content = document.get("content");

            if (method != null && path != null && headers != null && data != null) {
                Map<String, String> data_to_send = new HashMap<>();
                data_to_send.put("method", method);
                data_to_send.put("path", path);
                data_to_send.put("headers", headers);
                data_to_send.put("data", data);

                if (content != null) {
                    data_to_send.put("content", content);
                }

                Gson gsonObj = new Gson();

                Map<String, String> event_data = new HashMap<>();
                event_data.put("ip", document.get("ip"));
                event_data.put("user-agent", document.get("user-agent"));

                data_to_send.put("event", gsonObj.toJson(event_data));

                String json_string_gson = gsonObj.toJson(data_to_send);

                Long start = System.currentTimeMillis();
                String waf_response_str = Utils.sendPOST(con, json_string_gson);
                Float time_spent = (float) (System.currentTimeMillis() - start) / 1000;

                document.put("waf_replay_time_spent", time_spent.toString());
                document.put("performed_waf_review", "REPLAY");
                document.put("waf_replay_answer", waf_response_str);

                Type mapType = new TypeToken<Map<String, String>>() {}.getType();
                Map<String, String> waf_response = new Gson().fromJson(waf_response_str, mapType);

                if (waf_response.containsKey("status")) {
                    document.put("waf_status", waf_response.get("status"));
                }
            }
        }

        return document;
    }

    static class ProcessEnrichment extends DoFn<KV<String, Map<String, String>>, Map<String, String>> {
        private static URL url_obj;
        private static String waf_host = "10.132.0.14";

        @Setup
        public void setup() throws Exception {
            this.url_obj = new URL("http://" + this.waf_host + ":8080/process_request");
        }

        @ProcessElement
        public void process(ProcessContext c) throws Exception {
            HttpURLConnection con = (HttpURLConnection) this.url_obj.openConnection();
            KV<String, Map<String, String>> document_kv = c.element();
            Map<String, String> document = document_kv.getValue();
            Map<String, String> new_event = PerformWafEnrichment(document, con);
            c.output(new_event);
            con.disconnect();
        }
    }
}
