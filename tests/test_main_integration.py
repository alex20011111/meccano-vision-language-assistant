import contextlib
import io
import itertools
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_composition import Fixture, part
import meccano_tracker as tracker
from composition_controller import CompositionController, EmptyAreaGuard


class Tensor:
    def __init__(self, values): self.values=np.array(values)
    def cpu(self): return self
    def numpy(self): return self.values


def boxes_for(pieces, tracked):
    class_ids={"A003":0,"A045":1,"C658":2}
    return SimpleNamespace(xyxy=Tensor([p["bbox"] for p in pieces]),
                           cls=Tensor([class_ids[p["class_name"]] for p in pieces]),
                           conf=Tensor([0.9]*len(pieces)),is_track=tracked,
                           id=Tensor([p["tid"] for p in pieces]) if tracked else None)


class MainIntegrationTests(Fixture):
    def test_full_loop_keyboard_start_verify_and_guarded_change(self):
        controllers=[]
        class Controller(CompositionController):
            def __init__(self,guide):
                super().__init__(guide,stable_frames=1,
                                 guard=EmptyAreaGuard(min_frames=1,min_seconds=0,max_gap=5))
                controllers.append(self)
        class Frame:
            def __init__(self,array): self.array=array
            def get_data(self): return self.array
        class Pipeline:
            stopped=False
            def start(self,config):
                intrinsics=SimpleNamespace(fx=600)
                stream=SimpleNamespace(as_video_stream_profile=lambda:SimpleNamespace(get_intrinsics=lambda:intrinsics))
                sensor=SimpleNamespace(get_depth_scale=lambda:0.001)
                return SimpleNamespace(get_stream=lambda s:stream,
                                       get_device=lambda:SimpleNamespace(first_depth_sensor=lambda:sensor))
            def wait_for_frames(self):
                return SimpleNamespace(get_depth_frame=lambda:Frame(np.full((720,1280),600,np.uint16)),
                                       get_color_frame=lambda:Frame(np.zeros((720,1280,3),np.uint8)))
            def stop(self): self.stopped=True
        pipeline=Pipeline()
        rs=SimpleNamespace(pipeline=lambda:pipeline,
                           config=lambda:SimpleNamespace(enable_stream=lambda *a:None),
                           stream=SimpleNamespace(depth=0,color=1),
                           format=SimpleNamespace(z16=0,bgr8=1),
                           align=lambda s:SimpleNamespace(process=lambda f:f),
                           option=SimpleNamespace(filter_magnitude=0,filter_smooth_alpha=1,
                                                  filter_smooth_delta=2,holes_fill=3),
                           rs2_deproject_pixel_to_point=lambda *a:(0.1,0.1,0.6))
        filt=lambda:SimpleNamespace(process=lambda f:f,set_option=lambda *a:None)
        rs.spatial_filter=rs.temporal_filter=rs.hole_filling_filter=filt
        models=[]
        class Model:
            names={0:"A003",1:"A045",2:"C658"}
            def __init__(self,path):
                self.callbacks=[];self.frame=-1;self.kwargs=[];models.append(self)
            def add_callback(self,event,callback): self.callbacks.append(callback)
            def track(self,**kwargs):
                self.frame+=1;self.kwargs.append(kwargs)
                left=[part("A003",tid=1,cx=120),part("A045",tid=2,cx=260)]


                raw=left+[part("C658",tid=99,cx=900)] if self.frame in (2,3,4) else left
                predictor=SimpleNamespace(results=[SimpleNamespace(boxes=boxes_for(raw,False))])
                for callback in self.callbacks: callback(predictor)
                return [SimpleNamespace(boxes=boxes_for(left,True))]
        keys=iter([ord('g'),ord('n'),ord('v'),ord('n'),255,ord('n'),ord('q')])
        clock=itertools.count(0,0.1)
        model_path=self.directory/'best.pt';model_path.write_bytes(b'fake model')
        args=SimpleNamespace(model=str(model_path),silhouettes=str(self.directory),
                             tracker='bytetrack.yaml',no_voice=True)
        output=io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules,{'pyrealsense2':rs,'ultralytics':SimpleNamespace(YOLO=Model)}))
            for name,value in [('CompositionController',Controller),('COLOR_WIDTH',1280),('COLOR_HEIGHT',720),
                               ('LOCK_AFTER_FRAMES',1),('HISTORY_SIZE',2)]:
                stack.enter_context(patch.object(tracker,name,value))
            stack.enter_context(patch.object(tracker,'_arguments',return_value=args))
            stack.enter_context(patch.object(tracker.time,'monotonic',side_effect=lambda:next(clock)))
            stack.enter_context(patch.object(tracker.CompositionUI,'open'))
            stack.enter_context(patch.object(tracker.cv2,'imshow'))
            stack.enter_context(patch.object(tracker.cv2,'waitKey',side_effect=lambda n:next(keys)))
            stack.enter_context(patch.object(tracker.cv2,'getWindowProperty',return_value=1))
            stack.enter_context(patch.object(tracker.cv2,'destroyAllWindows'))
            stack.enter_context(contextlib.redirect_stdout(output))
            tracker.main()
        self.assertTrue(pipeline.stopped)
        self.assertEqual(len(controllers),1)
        self.assertEqual(controllers[0].generation,2)
        self.assertEqual(len(controllers[0].guide.slots),2)
        self.assertIn('Piano destro occupato',output.getvalue())
        self.assertIn('[VERIFICA]',output.getvalue())
        self.assertEqual(len(models[0].kwargs),7)
        for options in models[0].kwargs:
            self.assertFalse(options['save'])
            self.assertFalse(options['save_txt'])
            self.assertFalse(options['save_crop'])


if __name__=='__main__': unittest.main()
