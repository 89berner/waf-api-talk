package org.waf.pipeline;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import org.apache.beam.sdk.transforms.DoFn;

import java.lang.reflect.Type;
import java.util.HashMap;
import java.util.Map;

public class EventParser {
    static class ParseAndCreateDocumentFn extends DoFn<String, Map<String, String>> {
        @ProcessElement
        public void processElement(ProcessContext c) {
            String event = c.element();
            Map<String, String> document = new HashMap<>();

            Type mapType = new TypeToken<Map<String, String>>(){}.getType();
            document = new Gson().fromJson(event, mapType);

            for (String key : document.keySet()) {
                if (document.get(key) == null) {
                    document.put(key, "NULL");
                }
            }

            c.output(document);
        }
    }
}