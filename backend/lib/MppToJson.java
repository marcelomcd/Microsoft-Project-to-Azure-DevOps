import org.mpxj.reader.UniversalProjectReader;
import org.mpxj.json.JsonWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

public class MppToJson {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Uso: java MppToJson <arquivo.mpp> <arquivo.json>");
            System.exit(1);
        }
        
        try {
            String mppFile = args[0];
            String jsonFile = args[1];
            
            UniversalProjectReader reader = new UniversalProjectReader();
            var project = reader.read(new File(mppFile));
            
            OutputStream outputStream = new FileOutputStream(jsonFile);
            JsonWriter jsonWriter = new JsonWriter();
            jsonWriter.write(project, outputStream);
            outputStream.close();
            
            System.out.println("OK");
        } catch (Exception e) {
            System.err.println("Erro: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
