import contextlib
import io
import itertools
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

import numpy as np
from test_composition import Fixture, part
from test_main_integration import boxes_for
from assembly_guide_cad import CadAssemblyGuide
from composition_controller import CompositionController, EmptyAreaGuard, RETURN_PARTS_MESSAGE
from voice_assistant import SceneState
import meccano_tracker as tracker


class NewWorkflowTests(Fixture):
    def execute(self, invalid_frames=frozenset()):
        controllers=[]; voices=[]; models=[]; stabilizers=[]; rendered=[]; states=[]; views=[]
        class Controller(CompositionController):
            def __init__(self,guide):
                super().__init__(guide,stable_frames=1,guard=EmptyAreaGuard(min_frames=1,min_seconds=0))
                controllers.append(self)
        class Pipeline:
            frame=-1; stopped=False
            def start(self,config):
                intrinsics=SimpleNamespace(fx=600)
                stream=SimpleNamespace(as_video_stream_profile=lambda:SimpleNamespace(get_intrinsics=lambda:intrinsics))
                return SimpleNamespace(get_stream=lambda s:stream,get_device=lambda:SimpleNamespace(
                    first_depth_sensor=lambda:SimpleNamespace(get_depth_scale=lambda:0.001)))
            def wait_for_frames(self):
                self.frame+=1
                if self.frame in invalid_frames:
                    return SimpleNamespace(get_depth_frame=lambda:None,get_color_frame=lambda:None)
                return SimpleNamespace(get_depth_frame=lambda:SimpleNamespace(get_data=lambda:np.full((720,1280),600,np.uint16)),
                                       get_color_frame=lambda:SimpleNamespace(get_data=lambda:np.full((720,1280,3),60,np.uint8)))
            def stop(self):self.stopped=True
        pipeline=Pipeline()
        rs=SimpleNamespace(pipeline=lambda:pipeline,config=lambda:SimpleNamespace(enable_stream=lambda *a:None),
                           stream=SimpleNamespace(depth=0,color=1),format=SimpleNamespace(z16=0,bgr8=1),
                           align=lambda s:SimpleNamespace(process=lambda f:f),
                           option=SimpleNamespace(filter_magnitude=0,filter_smooth_alpha=1,filter_smooth_delta=2,holes_fill=3),
                           rs2_deproject_pixel_to_point=lambda *a:(0.1,0.1,0.6))
        rs.spatial_filter=rs.temporal_filter=rs.hole_filling_filter=lambda:SimpleNamespace(
            process=lambda f:f,set_option=lambda *a:None)
        class Model:
            names={0:'A003',1:'A045',2:'C658'}
            def __init__(self,path):self.callbacks=[];self.kwargs=[];self.targets=None;models.append(self)
            def add_callback(self,event,callback):self.callbacks.append(callback)
            def track(self,**kwargs):
                self.kwargs.append(kwargs)
                left=[part('A045',tid=1,cx=140),part('C658',tid=2,cx=320)]
                f=pipeline.frame
                if f<=2 or f>=9:
                    pieces=left
                else:
                    if self.targets is None:
                        self.targets=[part(s.code,tid=1 if s.code=='A045' else 2,cx=s.cx,cy=s.cy) for s in controllers[0].guide.slots]
                    pieces=[dict(p) for p in self.targets]
                    if f==3:
                        pieces=[p if p['tid']==1 else left[1] for p in pieces]
                raw=pieces
                tracked=[] if f==8 else pieces
                pred=SimpleNamespace(results=[SimpleNamespace(boxes=boxes_for(raw,False))])
                for callback in self.callbacks:callback(pred)
                return [SimpleNamespace(boxes=boxes_for(tracked,True))]
        class Voice:
            state='IDLE';last_error='';closed=False
            def __init__(self,*a,**k):self.spoken=[];self.stops=[];self.tag=None;voices.append(self)
            def is_busy(self):return self.state!='IDLE'
            def trigger(self):self.state='LISTENING';return True
            def say_async(self,text,interrupt=False,tag=None):
                if self.is_busy() and not interrupt:return False
                self.state='SPEAKING';self.tag=tag;self.spoken.append((pipeline.frame,text,interrupt));return True
            def stop(self):self.stops.append(pipeline.frame);self.state='IDLE';self.tag=None
            def cancel_tag(self,tag):
                if self.tag==tag:self.stop();return True
                return False
            def close(self):self.stop();self.closed=True
        class Stabilizer(tracker.ClassStabilizer):
            def __init__(self,**kwargs):super().__init__(**kwargs);stabilizers.append(self)
        def guide(*a,**k):return CadAssemblyGuide(*a,**k,stability_frames=2)
        original_draw=tracker.draw_detection
        def draw(image,d):
            rendered.append((pipeline.frame,d['tid'],d['locked']))
            return original_draw(image,d)
        def imshow(name,image):
            c=controllers[0]
            states.append((pipeline.frame,c.guide.generated,c.verification_visible,c.return_warning_visible,c.frame_valid))
            views.append((pipeline.frame,image.copy()))
        keys=iter([ord('g'),ord('r'),ord('v'),255,255,ord('x'),ord('s'),ord('g'),255,ord('g'),255,ord('q')])
        model_path=self.directory/'best.pt';model_path.write_bytes(b'fake')
        args=SimpleNamespace(model=str(model_path),silhouettes=str(self.directory),tracker='bytetrack.yaml',no_voice=False)
        clock=itertools.count(0,0.1);output=io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules,{'pyrealsense2':rs,'ultralytics':SimpleNamespace(YOLO=Model),
                'voice_assistant':SimpleNamespace(SceneState=SceneState,VoiceAssistant=Voice)}))
            for name,value in [('CompositionController',Controller),('ClassStabilizer',Stabilizer),('CadAssemblyGuide',guide),
                               ('COLOR_WIDTH',1280),('COLOR_HEIGHT',720),('LOCK_AFTER_FRAMES',1),('HISTORY_SIZE',2),('draw_detection',draw)]:
                stack.enter_context(patch.object(tracker,name,value))
            stack.enter_context(patch.object(tracker,'_arguments',return_value=args))
            stack.enter_context(patch.object(tracker.time,'monotonic',side_effect=lambda:next(clock)))
            stack.enter_context(patch.object(tracker.CompositionUI,'open'))
            stack.enter_context(patch.object(tracker.cv2,'imshow',side_effect=imshow))
            stack.enter_context(patch.object(tracker.cv2,'waitKey',side_effect=lambda n:next(keys)))
            stack.enter_context(patch.object(tracker.cv2,'getWindowProperty',return_value=1))
            stack.enter_context(patch.object(tracker.cv2,'destroyAllWindows'))
            stack.enter_context(contextlib.redirect_stdout(output))
            tracker.main()
        return SimpleNamespace(controllers=controllers,voices=voices,models=models,stabilizers=stabilizers,
                               rendered=rendered,states=states,views=views,output=output.getvalue(),pipeline=pipeline)

    def test_x_stop_warning_tracking_and_restart_in_real_main(self):
        result=self.execute();c=result.controllers[0];v=result.voices[0]
        self.assertTrue(result.pipeline.stopped);self.assertTrue(v.closed)
        self.assertEqual(c.generation,2)
        self.assertEqual(len(result.stabilizers),1)
        self.assertEqual(result.stabilizers[0].locked,{1:1,2:2})
        notice=[row for row in v.spoken if row[1]==RETURN_PARTS_MESSAGE]
        self.assertEqual(len(notice),1)
        self.assertTrue(notice[0][2])
        self.assertIn(6,v.stops)
        frames={s[0]:s[1:] for s in result.states}
        self.assertTrue(frames[3][1])
        self.assertTrue(frames[5][0])
        self.assertFalse(frames[6][0])
        self.assertTrue(frames[6][2]);self.assertTrue(frames[8][2])
        self.assertFalse(frames[9][2])
        for frame in (3,4,5,6,7,9,10):
            self.assertEqual({tid for f,tid,_ in result.rendered if f==frame},{1,2})
        self.assertIn('Piano destro occupato',result.output)
        for kwargs in result.models[0].kwargs:
            self.assertTrue(kwargs['persist']);self.assertFalse(kwargs['save'])

    def test_stop_and_finish_work_even_when_current_camera_frame_is_invalid(self):
        result=self.execute(invalid_frames={6});frames={s[0]:s[1:] for s in result.states}
        self.assertIn(6,result.voices[0].stops)
        self.assertFalse(frames[6][0])
        self.assertTrue(frames[6][2])
        self.assertFalse(frames[6][3])
        self.assertTrue(result.pipeline.stopped)
        self.assertEqual(result.controllers[0].generation,2)
